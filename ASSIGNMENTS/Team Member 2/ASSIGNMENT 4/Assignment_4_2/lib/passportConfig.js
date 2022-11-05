import passport from "passport";
import { Strategy } from "passport-local";

import passportJWT from "passport-jwt";
const JWTStrategy = passportJWT.Strategy;
const ExtractJWT = passportJWT.ExtractJwt;

import User from "../db/User.js";
import { jwtSecretKey } from "../lib/authKeys.js";

const filterJson = (obj, unwantedKeys) => {
  const filteredObj = {};
  Object.keys(obj).forEach((key) => {
    if (unwantedKeys.indexOf(key) === -1) {
      filteredObj[key] = obj[key];
    }
  });
  return filteredObj;
};

passport.use(
  new Strategy(
    {
      usernameField: "email",
      passReqToCallback: true,
    },
    (req, email, password, done, res) => {
      // console.log(email, password);
      User.findOne({ email: email }, (err, user) => {
        if (err) {
          return done(err);
        }
        if (!user) {
          return done(null, false, {
            message: "User does not exist",
          });
        }

        user
          .login(password)
          .then(() => {
            // let userSecure = {};
            // const unwantedKeys = ["password", "__v"];
            // Object.keys(user["_doc"]).forEach((key) => {
            //   if (unwantedKeys.indexOf(key) === -1) {
            //     userSecure[key] = user[key];
            //   }
            // });
            user["_doc"] = filterJson(user["_doc"], ["password", "__v"]);
            return done(null, user);
          })
          .catch((err) => {
            return done(err, false, {
              message: "Password is incorrect.",
            });
          });
      });
    }
  )
);

passport.use(
  new JWTStrategy(
    {
      jwtFromRequest: ExtractJWT.fromAuthHeaderAsBearerToken(),
      secretOrKey: jwtSecretKey,
    },
    (jwt_payload, done) => {
      User.findById(jwt_payload._id)
        .then((user) => {
          console.log(Object.keys(jwt_payload));
          if (!user) {
            return done(null, false, {
              message: "JWT Token does not exist",
            });
          }
          user["_doc"] = filterJson(user["_doc"], ["password", "__v"]);
          return done(null, user);
        })
        .catch((err) => {
          return done(err, false, {
            message: "Incorrect Token",
          });
        });
    }
  )
);

export default passport;
